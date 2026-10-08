package com.ems.dto;

import com.ems.entity.Employee;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;

/**
 * Outbound representation of an {@link Employee}. Never the persistence entity itself.
 */
public record EmployeeResponse(
		Long id,
		String firstName,
		String lastName,
		String email,
		String phone,
		String department,
		String designation,
		BigDecimal salary,
		LocalDate joiningDate,
		String status,
		Instant createdAt,
		Instant updatedAt) {

	public static EmployeeResponse fromEntity(Employee employee) {
		return new EmployeeResponse(
				employee.getId(),
				employee.getFirstName(),
				employee.getLastName(),
				employee.getEmail(),
				employee.getPhone(),
				employee.getDepartment(),
				employee.getDesignation(),
				employee.getSalary(),
				employee.getJoiningDate(),
				employee.getStatus(),
				employee.getCreatedAt(),
				employee.getUpdatedAt());
	}
}
