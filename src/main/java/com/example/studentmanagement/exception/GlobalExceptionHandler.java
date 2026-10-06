package com.example.studentmanagement.exception;

import com.example.studentmanagement.dto.ErrorResponse;
import jakarta.servlet.http.HttpServletRequest;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.http.converter.HttpMessageNotReadableException;

@RestControllerAdvice
public class GlobalExceptionHandler {
    private static final Logger LOGGER = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    @ExceptionHandler({MethodArgumentNotValidException.class, HttpMessageNotReadableException.class, IllegalArgumentException.class})
    public ResponseEntity<ErrorResponse> badRequest(Exception exception, HttpServletRequest request) { return error("VALIDATION_ERROR", "Request validation failed", HttpStatus.BAD_REQUEST, request); }
    @ExceptionHandler(StudentNotFoundException.class) public ResponseEntity<ErrorResponse> notFound(Exception exception, HttpServletRequest request) { return error("NOT_FOUND", "Requested resource was not found", HttpStatus.NOT_FOUND, request); }
    @ExceptionHandler(AuthenticationException.class) public ResponseEntity<ErrorResponse> unauthorized(Exception exception, HttpServletRequest request) { return error("UNAUTHORIZED", "Authentication is required", HttpStatus.UNAUTHORIZED, request); }
    @ExceptionHandler(AccessDeniedException.class) public ResponseEntity<ErrorResponse> forbidden(Exception exception, HttpServletRequest request) { return error("FORBIDDEN", "You do not have permission for this operation", HttpStatus.FORBIDDEN, request); }
    @ExceptionHandler(InvalidRefreshTokenException.class) public ResponseEntity<ErrorResponse> conflict(Exception exception, HttpServletRequest request) { return error("INVALID_REFRESH_TOKEN", "Refresh token is invalid, expired, or revoked", HttpStatus.CONFLICT, request); }
    @ExceptionHandler(Exception.class) public ResponseEntity<ErrorResponse> unexpected(Exception exception, HttpServletRequest request) { LOGGER.error("Unexpected request failure requestId={}", request.getAttribute("correlationId"), exception); return error("INTERNAL_ERROR", "An unexpected server error occurred", HttpStatus.INTERNAL_SERVER_ERROR, request); }
    private ResponseEntity<ErrorResponse> error(String code, String message, HttpStatus status, HttpServletRequest request) { return ResponseEntity.status(status).body(new ErrorResponse(code, message, status.value(), Instant.now(), String.valueOf(request.getAttribute("correlationId")))); }
}
