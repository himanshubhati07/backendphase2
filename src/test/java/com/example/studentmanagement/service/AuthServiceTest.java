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
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.core.Authentication;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AuthServiceTest {
    private final AuthenticationManager authenticationManager = mock(AuthenticationManager.class);
    private final JwtService jwtService = mock(JwtService.class);
    private final RefreshTokenRepository refreshTokenRepository = mock(RefreshTokenRepository.class);
    private final UserRepository userRepository = mock(UserRepository.class);
    private final User user = mock(User.class);
    private final AuthService service = new AuthService(authenticationManager, jwtService, properties(), refreshTokenRepository, userRepository);

    @Test void loginAuthenticatesAndReturnsNewTokenPair() {
        Authentication authentication = mock(Authentication.class);
        when(authenticationManager.authenticate(any())).thenReturn(authentication);
        when(authentication.getName()).thenReturn("admin");
        when(userRepository.findByUsername("admin")).thenReturn(Optional.of(user));
        when(user.getUsername()).thenReturn("admin");
        when(jwtService.generateAccessToken(any(), any())).thenReturn("access-token");

        TokenResponse response = service.login(new LoginRequest("admin", "password"));

        assertEquals("access-token", response.accessToken());
        ArgumentCaptor<RefreshToken> token = ArgumentCaptor.forClass(RefreshToken.class);
        verify(refreshTokenRepository).save(token.capture());
        assertEquals(user, token.getValue().getOwner());
    }

    @Test void refreshRotatesTokenAndRejectsItsReuse() {
        RefreshToken existing = new RefreshToken("old-token", Instant.now().plusSeconds(60), user);
        when(refreshTokenRepository.findByTokenValueForUpdate("old-token")).thenReturn(Optional.of(existing));
        when(user.getUsername()).thenReturn("admin");
        when(jwtService.generateAccessToken(any(), any())).thenReturn("new-access-token");

        TokenResponse response = service.refresh("old-token");

        assertEquals("new-access-token", response.accessToken());
        assertNotEquals("old-token", response.refreshToken());
        assertThrows(InvalidRefreshTokenException.class, () -> service.refresh("old-token"));
    }

    private JwtProperties properties() {
        JwtProperties properties = new JwtProperties();
        properties.setRefreshTokenExpirationMinutes(60);
        return properties;
    }
}
