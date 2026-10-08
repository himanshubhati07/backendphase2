package com.ems.service;

import com.ems.dto.AuthResponse;
import com.ems.dto.LoginRequest;
import com.ems.dto.RegisterRequest;
import com.ems.entity.User;
import com.ems.exception.DuplicateResourceException;
import com.ems.repository.UserRepository;
import com.ems.security.JwtService;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Account registration and credential-based login, both resulting in a freshly-issued
 * JWT access token. There is no RBAC and no refresh-token flow in this system.
 */
@Service
public class AuthService {

	private static final Logger log = LoggerFactory.getLogger(AuthService.class);

	private final UserRepository userRepository;
	private final PasswordEncoder passwordEncoder;
	private final JwtService jwtService;

	public AuthService(UserRepository userRepository, PasswordEncoder passwordEncoder, JwtService jwtService) {
		this.userRepository = userRepository;
		this.passwordEncoder = passwordEncoder;
		this.jwtService = jwtService;
	}

	@Transactional
	public AuthResponse register(RegisterRequest request) {
		if (userRepository.existsByEmail(request.email())) {
			throw new DuplicateResourceException("A user with email '" + request.email() + "' already exists");
		}

		User user = new User(request.email(), passwordEncoder.encode(request.password()), Instant.now());
		User saved = userRepository.save(user);
		log.info("Registered new user id={}", saved.getId());

		return issueToken(saved);
	}

	public AuthResponse login(LoginRequest request) {
		User user = userRepository
				.findByEmail(request.email())
				.orElseThrow(() -> new BadCredentialsException("Invalid email or password"));

		if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
			throw new BadCredentialsException("Invalid email or password");
		}

		log.info("User id={} logged in", user.getId());
		return issueToken(user);
	}

	private AuthResponse issueToken(User user) {
		String token = jwtService.generateToken(user);
		long expiresInSeconds = jwtService.getExpiryMinutes() * 60;
		return AuthResponse.of(token, expiresInSeconds);
	}
}
