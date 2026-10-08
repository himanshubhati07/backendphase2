package com.ems.exception;

import com.ems.dto.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import java.util.UUID;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Single, centralized place turning every exception the application can throw into
 * an HTTP response wrapped in {@link ApiResponse}. No controller or service in this
 * codebase should ever catch an exception just to hand-build its own error JSON.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

	private static final String CORRELATION_HEADER = "X-Correlation-ID";
	private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

	@ExceptionHandler(MethodArgumentNotValidException.class)
	public ResponseEntity<ApiResponse<Void>> handleValidation(
			MethodArgumentNotValidException ex, HttpServletRequest request) {
		String correlationId = correlationId(request);
		String message =
				ex.getBindingResult().getFieldErrors().stream()
						.map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
						.collect(Collectors.joining("; "));
		if (message.isBlank()) {
			message = "Validation failed";
		}
		log.warn("[{}] Validation failed on {}: {}", correlationId, request.getRequestURI(), message);
		return respond(HttpStatus.BAD_REQUEST, message, correlationId);
	}

	@ExceptionHandler(ResourceNotFoundException.class)
	public ResponseEntity<ApiResponse<Void>> handleNotFound(
			ResourceNotFoundException ex, HttpServletRequest request) {
		String correlationId = correlationId(request);
		log.info("[{}] Resource not found on {}: {}", correlationId, request.getRequestURI(), ex.getMessage());
		return respond(HttpStatus.NOT_FOUND, ex.getMessage(), correlationId);
	}

	@ExceptionHandler(DuplicateResourceException.class)
	public ResponseEntity<ApiResponse<Void>> handleDuplicate(
			DuplicateResourceException ex, HttpServletRequest request) {
		String correlationId = correlationId(request);
		log.warn("[{}] Duplicate resource on {}: {}", correlationId, request.getRequestURI(), ex.getMessage());
		return respond(HttpStatus.CONFLICT, ex.getMessage(), correlationId);
	}

	@ExceptionHandler({BadCredentialsException.class, AuthenticationException.class})
	public ResponseEntity<ApiResponse<Void>> handleAuthentication(
			Exception ex, HttpServletRequest request) {
		String correlationId = correlationId(request);
		log.warn("[{}] Authentication failed on {}: {}", correlationId, request.getRequestURI(), ex.getMessage());
		return respond(HttpStatus.UNAUTHORIZED, "Invalid credentials or token", correlationId);
	}

	@ExceptionHandler(AccessDeniedException.class)
	public ResponseEntity<ApiResponse<Void>> handleAccessDenied(
			AccessDeniedException ex, HttpServletRequest request) {
		String correlationId = correlationId(request);
		log.warn("[{}] Access denied on {}: {}", correlationId, request.getRequestURI(), ex.getMessage());
		return respond(HttpStatus.FORBIDDEN, "Access denied", correlationId);
	}

	@ExceptionHandler(Exception.class)
	public ResponseEntity<ApiResponse<Void>> handleUnexpected(Exception ex, HttpServletRequest request) {
		String correlationId = correlationId(request);
		log.error("[{}] Unhandled exception on {}", correlationId, request.getRequestURI(), ex);
		return respond(HttpStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred", correlationId);
	}

	private ResponseEntity<ApiResponse<Void>> respond(HttpStatus status, String message, String correlationId) {
		return ResponseEntity.status(status)
				.header(CORRELATION_HEADER, correlationId)
				.body(ApiResponse.error(message));
	}

	private String correlationId(HttpServletRequest request) {
		String incoming = request.getHeader(CORRELATION_HEADER);
		if (incoming == null || incoming.isBlank()) {
			incoming = request.getHeader("X-Request-ID");
		}
		return (incoming == null || incoming.isBlank()) ? UUID.randomUUID().toString() : incoming;
	}
}
