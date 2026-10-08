package com.ems.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

/**
 * Payload for {@code POST /api/v1/auth/login}.
 */
public record LoginRequest(
		@NotBlank(message = "email is required") @Email(message = "email must be a valid address") String email,
		@NotBlank(message = "password is required") String password) {}
