package com.example.studentmanagement.kafka;

import com.example.studentmanagement.dto.StudentResponse;
import java.time.Instant;
public record StudentEvent(StudentEventType type, Long studentId, Instant occurredAt, StudentResponse student) { }
