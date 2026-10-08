package com.ems.websocket;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

/**
 * Scaffold WebSocket endpoint for future event-driven extensions (e.g. pushing
 * employee lifecycle notifications to connected clients). Currently just echoes
 * received text frames back to the sender and logs connection lifecycle events -
 * no employee business logic is wired to it yet.
 */
@Component
public class NotificationWebSocketHandler extends TextWebSocketHandler {

	private static final Logger log = LoggerFactory.getLogger(NotificationWebSocketHandler.class);

	@Override
	public void afterConnectionEstablished(WebSocketSession session) {
		log.info("WebSocket connection established: sessionId={}", session.getId());
	}

	@Override
	protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
		log.debug("WebSocket message received: sessionId={}, payload={}", session.getId(), message.getPayload());
		session.sendMessage(new TextMessage("echo: " + message.getPayload()));
	}

	@Override
	public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
		log.info("WebSocket connection closed: sessionId={}, status={}", session.getId(), status);
	}

	@Override
	public void handleTransportError(WebSocketSession session, Throwable exception) {
		log.warn("WebSocket transport error: sessionId={}", session.getId(), exception);
	}
}
