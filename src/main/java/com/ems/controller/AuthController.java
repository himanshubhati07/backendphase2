package com.ems.controller;

import com.ems.dto.ApiResponse;
import com.ems.dto.AuthResponse;
import com.ems.dto.LoginRequest;
import com.ems.dto.RegisterRequest;
import com.ems.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Public, unauthenticated endpoints for account registration and login. Both issue a
 * JWT access token good for 30 minutes; there is no refresh-token endpoint.
 */
@RestController
@RequestMapping("/api/v1/auth")
@Tag(name = "Auth", description = "Registration and login")
public class AuthController {

	private final AuthService authService;

	public AuthController(AuthService authService) {
		this.authService = authService;
	}

	@PostMapping("/register")
	@Operation(summary = "Register a new user account")
	public ResponseEntity<ApiResponse<AuthResponse>> register(@Valid @RequestBody RegisterRequest request) {
		AuthResponse response = authService.register(request);
		return ResponseEntity.status(HttpStatus.CREATED)
				.body(ApiResponse.success("User registered successfully", response));
	}

	@PostMapping("/login")
	@Operation(summary = "Authenticate with email and password")
	public ResponseEntity<ApiResponse<AuthResponse>> login(@Valid @RequestBody LoginRequest request) {
		AuthResponse response = authService.login(request);
		return ResponseEntity.ok(ApiResponse.success("Login successful", response));
	}
}
