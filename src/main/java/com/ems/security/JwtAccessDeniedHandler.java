package com.ems.security;

import com.ems.dto.ApiResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

/**
 * Produces the 403 response for authenticated-but-forbidden requests at the filter
 * chain level, matching the same {@code ApiResponse} envelope shape used by
 * {@code GlobalExceptionHandler} for {@link AccessDeniedException}s raised inside
 * controllers/services.
 */
@Component
public class JwtAccessDeniedHandler implements AccessDeniedHandler {

	private final ObjectMapper objectMapper;

	public JwtAccessDeniedHandler(ObjectMapper objectMapper) {
		this.objectMapper = objectMapper;
	}

	@Override
	public void handle(
			HttpServletRequest request, HttpServletResponse response, AccessDeniedException accessDeniedException)
			throws IOException {
		response.setStatus(HttpServletResponse.SC_FORBIDDEN);
		response.setContentType(MediaType.APPLICATION_JSON_VALUE);
		response.getWriter().write(objectMapper.writeValueAsString(ApiResponse.error("Access denied")));
	}
}
