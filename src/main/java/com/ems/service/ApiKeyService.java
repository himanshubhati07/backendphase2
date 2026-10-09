package com.ems.service;

import com.ems.exception.ApiKeyException;
import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Validates the optional {@code api-key} query parameter accepted by security-sensitive
 * endpoints (currently {@code DELETE /api/v1/employees/{id}}). Valid keys are configured
 * via the comma-separated {@code app.api-key.keys} property; when that property is empty
 * or unset, validation is disabled and every call succeeds silently.
 */
@Service
public class ApiKeyService {

	private static final Logger log = LoggerFactory.getLogger(ApiKeyService.class);

	private final Set<String> validKeys;

	public ApiKeyService(@Value("${app.api-key.keys:}") String configuredKeys) {
		this.validKeys = Arrays.stream(configuredKeys.split(","))
				.map(String::trim)
				.filter(key -> !key.isEmpty())
				.collect(Collectors.toUnmodifiableSet());
	}

	/**
	 * Validates the given API key for an operation on the given employee id.
	 *
	 * @throws ApiKeyException if validation is enabled (at least one key configured) and
	 *     the supplied key is missing or does not match any configured key.
	 */
	public void validateApiKey(String apiKey, Long employeeId) {
		if (validKeys.isEmpty()) {
			// No keys configured: API key validation is disabled.
			return;
		}
		if (apiKey == null || apiKey.isBlank() || !validKeys.contains(apiKey)) {
			throw new ApiKeyException("Invalid or missing API key");
		}
		log.info("API key successfully validated for employee id={}", employeeId);
	}
}
