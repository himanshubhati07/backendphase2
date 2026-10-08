package com.ems.config;

import com.ems.security.JwtAccessDeniedHandler;
import com.ems.security.JwtAuthenticationEntryPoint;
import com.ems.security.JwtAuthenticationFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Wires up stateless JWT authentication for the whole API: every {@code /api/v1/**}
 * endpoint requires a valid bearer token except the auth endpoints themselves and the
 * documentation/health/websocket paths listed below. There is no RBAC, so
 * {@code AuthService} authenticates credentials directly against {@link PasswordEncoder}
 * rather than going through a Spring Security {@code AuthenticationManager}.
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

	private static final String[] PERMIT_ALL_PATTERNS = {
		"/api/v1/auth/**",
		"/swagger-ui/**",
		"/v3/api-docs/**",
		"/api-docs/**",
		"/docs/**",
		"/ws/**",
		"/health",
		"/actuator/health"
	};

	private final JwtAuthenticationFilter jwtAuthenticationFilter;
	private final JwtAuthenticationEntryPoint jwtAuthenticationEntryPoint;
	private final JwtAccessDeniedHandler jwtAccessDeniedHandler;

	public SecurityConfig(
			JwtAuthenticationFilter jwtAuthenticationFilter,
			JwtAuthenticationEntryPoint jwtAuthenticationEntryPoint,
			JwtAccessDeniedHandler jwtAccessDeniedHandler) {
		this.jwtAuthenticationFilter = jwtAuthenticationFilter;
		this.jwtAuthenticationEntryPoint = jwtAuthenticationEntryPoint;
		this.jwtAccessDeniedHandler = jwtAccessDeniedHandler;
	}

	@Bean
	public PasswordEncoder passwordEncoder() {
		return new BCryptPasswordEncoder();
	}

	@Bean
	public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
		http.csrf(AbstractHttpConfigurer::disable)
				.cors(Customizer.withDefaults())
				.sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
				.authorizeHttpRequests(auth -> auth.requestMatchers(PERMIT_ALL_PATTERNS)
						.permitAll()
						.anyRequest()
						.authenticated())
				.exceptionHandling(exception -> exception
						.authenticationEntryPoint(jwtAuthenticationEntryPoint)
						.accessDeniedHandler(jwtAccessDeniedHandler))
				.addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

		return http.build();
	}
}
