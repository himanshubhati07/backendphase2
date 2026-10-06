package com.example.studentmanagement.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record StudentRequest(@NotBlank String name, @NotBlank @Email String email, @NotBlank String phone,
                             @NotBlank String course, @NotNull @Positive Integer age) { }
