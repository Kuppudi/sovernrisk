from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import Country, ModelVersion, Prediction
from backend.app.schemas.api import IndicatorOut, MapCountryOut, MapDataOut, ModelStatus, PredictionOut


def _latest_model_version(db: Session) -> ModelVersion | None:
    return db.scalar(
        select(ModelVersion)
        .where(ModelVersion.model_name == "default_onset")
        .order_by(ModelVersion.trained_at.desc())
        .limit(1)
    )


def get_model_status(db: Session) -> ModelStatus:
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
        reason="Validated default-onset predictions are available for configured countries.",
    )


def get_country_prediction(db: Session, iso3: str) -> PredictionOut:
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
    )


def get_default_risk_map(db: Session, requested_year: int) -> MapDataOut:
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
    available_years = sorted({day.year for day in years}, reverse=True)
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
            Prediction.as_of_date >= datetime(target_year, 1, 1).date(),
            Prediction.as_of_date <= datetime(target_year, 12, 31).date(),
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
    )