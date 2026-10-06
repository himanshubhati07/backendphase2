package com.example.studentmanagement.security;

import com.example.studentmanagement.entity.Role;
import java.util.Set;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

class JwtServiceTest {
    @Test void tokenCarriesSubjectAndRejectsMalformedValue() {
        JwtProperties properties = new JwtProperties(); properties.setSecret("this-is-a-test-secret-that-is-at-least-thirty-two-bytes");
        JwtService service = new JwtService(properties); String token = service.generateAccessToken("admin", Set.of(Role.ADMIN));
        assertEquals("admin", service.extractUsername(token)); assertFalse(service.isValid("malformed"));
    }
}
