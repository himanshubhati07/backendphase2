package com.ems.exception;

/**
 * Raised when an optional API key supplied on a request (e.g. the {@code api-key}
 * query parameter on {@code DELETE /api/v1/employees/{id}}) is missing or does not
 * match any configured key. Translated to HTTP 401 by {@link GlobalExceptionHandler}.
 */
public class ApiKeyException extends RuntimeException {

	public ApiKeyException(String message) {
		super(message);
	}

	public ApiKeyException(String message, Throwable cause) {
		super(message, cause);
	}
}
