package com.ems.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Wires a Bearer-token security scheme into the generated OpenAPI spec so Swagger
 * UI (served at {@code /docs}) offers an "Authorize" button for the JWT access token.
 */
@Configuration
public class OpenApiConfig {

	private static final String BEARER_SCHEME_NAME = "bearerAuth";

	@Bean
	public OpenAPI employeeManagementOpenApi() {
		return new OpenAPI()
				.info(new Info()
						.title("Employee Management System API")
						.description("JWT-secured REST API for managing employees")
						.version("v1"))
				.addSecurityItem(new SecurityRequirement().addList(BEARER_SCHEME_NAME))
				.components(new Components()
						.addSecuritySchemes(
								BEARER_SCHEME_NAME,
								new SecurityScheme()
										.name(BEARER_SCHEME_NAME)
										.type(SecurityScheme.Type.HTTP)
										.scheme("bearer")
										.bearerFormat("JWT")));
	}
}
