package com.example.studentmanagement.dto;
import java.time.Instant;
public record ErrorResponse(String code, String message, int status, Instant timestamp, String correlationId) { }
