package com.ems.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.Date;
import java.util.function.Function;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Component;

/**
 * Issues and verifies the HS256 JWT access tokens used for stateless authentication.
 * Tokens carry the user's email as subject and expire after {@code app.jwt.expiry-minutes}
 * (30 minutes, fixed) with no refresh-token mechanism.
 */
@Component
public class JwtService {

	private final SecretKey signingKey;
	private final long expiryMinutes;

	public JwtService(
			@Value("${app.jwt.secret}") String secret, @Value("${app.jwt.expiry-minutes}") long expiryMinutes) {
		this.signingKey = Keys.hmacShaKeyFor(deriveKeyBytes(secret));
		this.expiryMinutes = expiryMinutes;
	}

	/**
	 * HS256 requires a key of at least 256 bits. A configured secret shorter than that
	 * would otherwise throw {@code WeakKeyException} at startup, so any secret is first
	 * stretched to a fixed 256-bit key via SHA-256 rather than used raw.
	 */
	private static byte[] deriveKeyBytes(String secret) {
		try {
			return MessageDigest.getInstance("SHA-256").digest(secret.getBytes(StandardCharsets.UTF_8));
		} catch (NoSuchAlgorithmException e) {
			throw new IllegalStateException("SHA-256 algorithm unavailable in this JVM", e);
		}
	}

	public String generateToken(UserDetails userDetails) {
		Instant now = Instant.now();
		Instant expiry = now.plusSeconds(expiryMinutes * 60);
		return Jwts.builder()
				.subject(userDetails.getUsername())
				.issuedAt(Date.from(now))
				.expiration(Date.from(expiry))
				.signWith(signingKey)
				.compact();
	}

	public long getExpiryMinutes() {
		return expiryMinutes;
	}

	public String extractEmail(String token) {
		return extractClaim(token, Claims::getSubject);
	}

	public boolean isTokenValid(String token, UserDetails userDetails) {
		String email = extractEmail(token);
		return email.equals(userDetails.getUsername()) && !isTokenExpired(token);
	}

	private boolean isTokenExpired(String token) {
		return extractClaim(token, Claims::getExpiration).before(Date.from(Instant.now()));
	}

	private <T> T extractClaim(String token, Function<Claims, T> resolver) {
		Claims claims = Jwts.parser().verifyWith(signingKey).build().parseSignedClaims(token).getPayload();
		return resolver.apply(claims);
	}

	/**
	 * Parses and validates the token's signature/expiration without binding it to a
	 * particular {@link UserDetails}, surfacing any failure as a {@link JwtException}.
	 */
	public void validateToken(String token) {
		Jwts.parser().verifyWith(signingKey).build().parseSignedClaims(token);
	}
}
