package com.example.studentmanagement.dto;

import jakarta.validation.constraints.NotBlank;
public record RefreshRequest(@NotBlank String refreshToken) { }
