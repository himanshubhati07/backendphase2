package com.example.studentmanagement.service;

import com.example.studentmanagement.dto.LoginRequest;
import com.example.studentmanagement.dto.TokenResponse;
import com.example.studentmanagement.entity.RefreshToken;
import com.example.studentmanagement.entity.User;
import com.example.studentmanagement.exception.InvalidRefreshTokenException;
import com.example.studentmanagement.repository.RefreshTokenRepository;
import com.example.studentmanagement.repository.UserRepository;
import com.example.studentmanagement.security.JwtProperties;
import com.example.studentmanagement.security.JwtService;
import java.time.Instant;
import java.util.UUID;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {
    private final AuthenticationManager authenticationManager;
    private final JwtService jwtService;
    private final JwtProperties properties;
    private final RefreshTokenRepository refreshTokenRepository;
    private final UserRepository userRepository;
    public AuthService(AuthenticationManager authenticationManager, JwtService jwtService, JwtProperties properties, RefreshTokenRepository refreshTokenRepository, UserRepository userRepository) { this.authenticationManager = authenticationManager; this.jwtService = jwtService; this.properties = properties; this.refreshTokenRepository = refreshTokenRepository; this.userRepository = userRepository; }
    @Transactional public TokenResponse login(LoginRequest request) {
        Authentication authentication = authenticationManager.authenticate(UsernamePasswordAuthenticationToken.unauthenticated(request.username(), request.password()));
        return issueForUsername(authentication.getName());
    }
    @Transactional public TokenResponse refresh(String value) {
        RefreshToken token = refreshTokenRepository.findByTokenValueForUpdate(value).orElseThrow(() -> new InvalidRefreshTokenException("Unknown refresh token"));
        if (token.isRevoked()) { throw new InvalidRefreshTokenException("Refresh token has been revoked"); }
        if (token.getExpiry().isBefore(Instant.now())) { throw new InvalidRefreshTokenException("Refresh token has expired"); }
        token.revoke();
        return issue(token.getOwner());
    }
    private TokenResponse issueForUsername(String username) {
        User user = userRepository.findByUsername(username).orElseThrow(() -> new InvalidRefreshTokenException("Authenticated user is unavailable"));
        return issue(user);
    }
    private TokenResponse issue(User user) {
        String refreshValue = UUID.randomUUID().toString();
        refreshTokenRepository.save(new RefreshToken(refreshValue, Instant.now().plusSeconds(properties.getRefreshTokenExpirationMinutes() * 60), user));
        return new TokenResponse(jwtService.generateAccessToken(user.getUsername(), user.getRoles()), refreshValue);
    }
}
