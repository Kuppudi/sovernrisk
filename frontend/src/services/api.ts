export function isWorldBankIndicator(code = ''): boolean {
  if (!code) return true
  if (code === 'default-risk') return false
  return !code.startsWith('IMF.') && !code.startsWith('ADB.')
}

export class ApiError extends Error {
  constructor(message: string, public status: number, public code: string) {
    super(message)
  }
}

export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, options)
  } catch {
    throw new Error(
      'The API could not be reached. Check that the backend is running.',
    )
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(
      body?.error?.message ||
        `Request failed (${response.status}). Check the backend and database.`,
      response.status,
      body?.error?.code || 'HTTP_ERROR',
    )
  }
  return response.json() as Promise<T>
}
