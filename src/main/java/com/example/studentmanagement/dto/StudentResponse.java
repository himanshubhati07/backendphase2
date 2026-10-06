package com.example.studentmanagement.dto;

public record StudentResponse(Long id, String name, String email, String phone, String course, Integer age) { }
