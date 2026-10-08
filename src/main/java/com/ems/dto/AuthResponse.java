package com.ems.dto;

/**
 * Response returned by both {@code /api/v1/auth/register} and {@code /api/v1/auth/login},
 * carrying the freshly-issued JWT access token.
 */
public record AuthResponse(String accessToken, String tokenType, long expiresInSeconds) {

	public static AuthResponse of(String accessToken, long expiresInSeconds) {
		return new AuthResponse(accessToken, "Bearer", expiresInSeconds);
	}
}
