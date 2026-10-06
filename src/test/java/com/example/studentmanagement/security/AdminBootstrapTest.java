package com.example.studentmanagement.security;

import com.example.studentmanagement.entity.Role;
import com.example.studentmanagement.entity.User;
import com.example.studentmanagement.repository.UserRepository;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.crypto.password.PasswordEncoder;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AdminBootstrapTest {
    private final UserRepository userRepository = mock(UserRepository.class);
    private final PasswordEncoder passwordEncoder = mock(PasswordEncoder.class);

    @Test
    void persistsConfiguredAdminWhenItDoesNotExist() throws Exception {
        when(userRepository.findByUsername("admin")).thenReturn(Optional.empty());
        when(passwordEncoder.encode("safe-password")).thenReturn("encoded-password");

        new AdminBootstrap(userRepository, passwordEncoder, "admin", "safe-password").run(null);

        ArgumentCaptor<User> user = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(user.capture());
        assertEquals("admin", user.getValue().getUsername());
        assertEquals("encoded-password", user.getValue().getPasswordHash());
        assertEquals(Role.ADMIN, user.getValue().getRoles().iterator().next());
    }

    @Test
    void retainsExistingAdminWithoutChangingItsPassword() throws Exception {
        when(userRepository.findByUsername("admin")).thenReturn(Optional.of(mock(User.class)));

        new AdminBootstrap(userRepository, passwordEncoder, "admin", "safe-password").run(null);

        verify(userRepository, never()).save(org.mockito.ArgumentMatchers.any());
        verify(passwordEncoder, never()).encode(org.mockito.ArgumentMatchers.any());
    }

    @Test
    void rejectsMissingBootstrapCredentials() {
        AdminBootstrap bootstrap = new AdminBootstrap(userRepository, passwordEncoder, "admin", " ");

        assertThrows(IllegalStateException.class, () -> bootstrap.run(null));
    }
}
