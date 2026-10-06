package com.example.studentmanagement.security;

import com.example.studentmanagement.entity.Role;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.Set;
import javax.crypto.SecretKey;
import org.springframework.stereotype.Service;

@Service
public class JwtService {
    private final JwtProperties properties;
    public JwtService(JwtProperties properties) { this.properties = properties; }
    public String generateAccessToken(String username, Set<Role> roles) {
        Instant now = Instant.now();
        return Jwts.builder().subject(username).claim("roles", roles.stream().map(role -> "ROLE_" + role.name()).toList())
                .issuedAt(Date.from(now)).expiration(Date.from(now.plusSeconds(properties.getAccessTokenExpirationMinutes() * 60))).signWith(key()).compact();
    }
    public String extractUsername(String token) { return parse(token).getSubject(); }
    public boolean isValid(String token) { try { parse(token); return true; } catch (RuntimeException exception) { return false; } }
    private Claims parse(String token) { return Jwts.parser().verifyWith(key()).build().parseSignedClaims(token).getPayload(); }
    private SecretKey key() {
        String secret = properties.getSecret();
        if (secret == null || secret.length() < 32) { throw new IllegalStateException("JWT signing material must be externally configured and at least 32 characters"); }
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }
}
