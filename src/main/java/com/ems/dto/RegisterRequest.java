package com.ems.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Payload for {@code POST /api/v1/auth/register}.
 */
public record RegisterRequest(
		@NotBlank(message = "email is required") @Email(message = "email must be a valid address") String email,
		@NotBlank(message = "password is required")
				@Size(min = 8, max = 100, message = "password must be between 8 and 100 characters")
				String password) {}
