package com.ems.security;

import com.ems.dto.ApiResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.http.MediaType;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.stereotype.Component;

/**
 * Produces the 401 response for requests that reach a protected endpoint without a
 * valid JWT, matching the same {@code ApiResponse} envelope shape that
 * {@code GlobalExceptionHandler} uses for authentication failures raised inside
 * controllers/services.
 */
@Component
public class JwtAuthenticationEntryPoint implements AuthenticationEntryPoint {

	private final ObjectMapper objectMapper;

	public JwtAuthenticationEntryPoint(ObjectMapper objectMapper) {
		this.objectMapper = objectMapper;
	}

	@Override
	public void commence(
			HttpServletRequest request, HttpServletResponse response, AuthenticationException authException)
			throws IOException {
		response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
		response.setContentType(MediaType.APPLICATION_JSON_VALUE);
		response.getWriter().write(objectMapper.writeValueAsString(ApiResponse.error("Invalid credentials or token")));
	}
}
