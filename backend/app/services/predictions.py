from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import Country, ModelVersion, Prediction
from backend.app.schemas.api import IndicatorOut, MapCountryOut, MapDataOut, ModelStatus, PredictionOut
from backend.app.services.observations import require_country
from backend.app.services.prediction_blobs import load_bundle


def _blob_bundle():
    url = get_settings().predictions_blob_url
    return load_bundle(url) if url else None


def _latest_model_version(db: Session) -> ModelVersion | None:
    return db.scalar(
        select(ModelVersion)
        .where(ModelVersion.model_name == "default_onset")
        .order_by(ModelVersion.trained_at.desc())
        .limit(1)
    )


def get_model_status(db: Session) -> ModelStatus:
    bundle = _blob_bundle()
    if bundle is not None:
        return ModelStatus(
            status="available", risk_model=f"default_onset:{bundle.model_version}",
            predictions_available=len(bundle.predictions),
            outcome_year=max(row.outcome_year for row in bundle.predictions),
            reason=f"Historical research results. {bundle.limitation}",
        )
    model = _latest_model_version(db)
    if model is None:
        return ModelStatus()

    prediction_count = db.scalar(
        select(func.count()).select_from(Prediction).where(Prediction.model_version_id == model.id)
    )
    if not prediction_count:
        return ModelStatus()

    return ModelStatus(
        status="available",
        risk_model=f"default_onset:{model.version}",
        downgrade_model="Model Not Trained",
        predictions_available=prediction_count,
        reason="Stored research predictions are available. These are not validated current forecasts.",
    )


def get_country_prediction(db: Session, iso3: str) -> PredictionOut:
    bundle = _blob_bundle()
    if bundle is not None:
        if not any(country.iso3 == iso3 for country in bundle.countries):
            raise HTTPException(404, {"code": "COUNTRY_NOT_FOUND", "message": "Country not found."})
        year = max(row.outcome_year for row in bundle.predictions)
        for row in bundle.predictions:
            if row.country_iso3 == iso3 and row.outcome_year == year:
                return row
        raise HTTPException(404, {
            "code": "PREDICTION_NOT_FOUND",
            "message": f"No eligible research prediction for this country in {year}.",
        })
    require_country(db, iso3)
    latest = _latest_model_version(db)
    if latest is None:
        raise HTTPException(
            503,
            {
                "code": "MODEL_NOT_TRAINED",
                "message": "No trained default-onset model is available.",
            },
        )

    row = db.scalar(
        select(Prediction)
        .where(
            Prediction.country_iso3 == iso3,
            Prediction.model_version_id == latest.id,
        )
        .order_by(Prediction.as_of_date.desc(), Prediction.generated_at.desc())
        .limit(1)
    )
    if row is None:
        raise HTTPException(
            404,
            {
                "code": "PREDICTION_NOT_FOUND",
                "message": "No stored prediction is available for this country.",
            },
        )

    return PredictionOut(
        country_iso3=row.country_iso3,
        as_of_date=row.as_of_date,
        risk_score=row.risk_score,
        downgrade_probability_12m=row.downgrade_probability_12m,
        model_version=latest.version,
        generated_at=row.generated_at,
        data_snapshot_id=row.data_snapshot_id,
        outcome_year=row.as_of_date.year + 1,
        feature_year=row.as_of_date.year - 1,
    )


def get_default_risk_map(db: Session, requested_year: int) -> MapDataOut:
    bundle = _blob_bundle()
    if bundle is not None:
        years = sorted({row.outcome_year for row in bundle.predictions}, reverse=True)
        year = requested_year if requested_year in years else years[0]
        values = {row.country_iso3: row for row in bundle.predictions if row.outcome_year == year}
        return MapDataOut(
            indicator=IndicatorOut(
                code="default-risk", name="Debt default risk", category="risk",
                unit="Probability", source_id=0,
                definition="Historical research probability of sovereign default onset.",
            ),
            year=year, available_years=years, research_only=True,
            countries=[MapCountryOut(
                **country.model_dump(),
                value=values[country.iso3].risk_score if country.iso3 in values else None,
                observation_year=year if country.iso3 in values else None,
                retrieved_at=bundle.generated_at if country.iso3 in values else None,
                dataset_version=bundle.dataset_version if country.iso3 in values else None,
            ) for country in bundle.countries],
            source_name=f"Local research model ({bundle.model_version})",
            source_url="",
        )
    latest = _latest_model_version(db)
    if latest is None:
        raise HTTPException(
            503,
            {
                "code": "MODEL_NOT_TRAINED",
                "message": "No trained default-onset model is available.",
            },
        )

    years = db.scalars(
        select(Prediction.as_of_date)
        .where(Prediction.model_version_id == latest.id)
        .distinct()
    ).all()
    available_years = sorted({day.year + 1 for day in years}, reverse=True)
    if not available_years:
        raise HTTPException(
            404,
            {
                "code": "PREDICTIONS_EMPTY",
                "message": "No stored predictions are available for map rendering.",
            },
        )

    target_year = requested_year if requested_year in available_years else available_years[0]
    rows = db.scalars(
        select(Prediction)
        .where(
            Prediction.model_version_id == latest.id,
            Prediction.as_of_date >= datetime(target_year - 1, 1, 1).date(),
            Prediction.as_of_date <= datetime(target_year - 1, 12, 31).date(),
        )
    ).all()
    values = {row.country_iso3: row for row in rows}

    countries = db.scalars(select(Country).order_by(Country.name)).all()
    map_countries = []
    for country in countries:
        prediction = values.get(country.iso3)
        map_countries.append(
            MapCountryOut(
                iso3=country.iso3,
                name=country.name,
                region=country.region,
                income_group=country.income_group,
                value=prediction.risk_score if prediction else None,
                observation_year=target_year if prediction else None,
                retrieved_at=prediction.generated_at if prediction else None,
                dataset_version=prediction.data_snapshot_id if prediction else None,
            )
        )

    indicator = IndicatorOut(
        code="default-risk",
        name="Debt default risk",
        category="risk",
        unit="Probability",
        source_id=0,
        definition="Stored model probability of sovereign default onset for the selected forecast window.",
    )
    return MapDataOut(
        indicator=indicator,
        year=target_year,
        available_years=available_years,
        countries=map_countries,
        source_name=f"SovereignRisk model ({latest.version})",
        source_url="local-training-artifact",
        research_only=True,
    )
