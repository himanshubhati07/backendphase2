package com.ems.security;

import com.ems.repository.UserRepository;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

/**
 * Backs Spring Security's {@link UserDetailsService} contract with the real
 * {@link UserRepository}. Registering this bean also suppresses Spring Boot's
 * auto-configured default in-memory user (and the generated-password log line that
 * comes with it) - this application never actually routes a login through Spring
 * Security's own {@code AuthenticationManager}; {@code AuthService} checks credentials
 * directly via {@code PasswordEncoder}, but a real {@link UserDetailsService} is still
 * the idiomatic way to tell Spring Security "accounts are managed, don't invent one."
 */
@Service
public class EmsUserDetailsService implements UserDetailsService {

	private final UserRepository userRepository;

	public EmsUserDetailsService(UserRepository userRepository) {
		this.userRepository = userRepository;
	}

	@Override
	public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
		return userRepository
				.findByEmail(email)
				.orElseThrow(() -> new UsernameNotFoundException("No user with email: " + email));
	}
}
