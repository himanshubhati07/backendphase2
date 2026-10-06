package com.example.studentmanagement.dto;

import java.util.List;
public record StudentPageResponse(List<StudentResponse> items, long total, int limit, long offset) { }
