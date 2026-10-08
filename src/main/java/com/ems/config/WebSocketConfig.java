package com.ems.config;

import com.ems.websocket.NotificationWebSocketHandler;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * Registers the {@link NotificationWebSocketHandler} scaffold at {@code /ws/notifications}.
 * This endpoint is explicitly excluded from JWT auth in {@code SecurityConfig} (see
 * the {@code /ws/**} permit-all rule).
 */
@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

	private final NotificationWebSocketHandler notificationWebSocketHandler;

	public WebSocketConfig(NotificationWebSocketHandler notificationWebSocketHandler) {
		this.notificationWebSocketHandler = notificationWebSocketHandler;
	}

	@Override
	public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
		registry.addHandler(notificationWebSocketHandler, "/ws/notifications").setAllowedOrigins("*");
	}
}
