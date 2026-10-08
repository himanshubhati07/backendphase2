package com.ems.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * Request payload for creating or updating an employee. Every field is required
 * except {@code phone}.
 */
public class EmployeeRequest {

	@NotBlank(message = "First name is required")
	@Size(max = 100, message = "First name must be at most 100 characters")
	private String firstName;

	@NotBlank(message = "Last name is required")
	@Size(max = 100, message = "Last name must be at most 100 characters")
	private String lastName;

	@NotBlank(message = "Email is required")
	@Email(message = "Email must be a valid email address")
	@Size(max = 255, message = "Email must be at most 255 characters")
	private String email;

	@Size(max = 50, message = "Phone must be at most 50 characters")
	private String phone;

	@NotBlank(message = "Department is required")
	@Size(max = 100, message = "Department must be at most 100 characters")
	private String department;

	@NotBlank(message = "Designation is required")
	@Size(max = 100, message = "Designation must be at most 100 characters")
	private String designation;

	@NotNull(message = "Salary is required")
	@DecimalMin(value = "0.0", inclusive = true, message = "Salary must not be negative")
	private BigDecimal salary;

	@NotNull(message = "Joining date is required")
	private LocalDate joiningDate;

	@NotBlank(message = "Status is required")
	@Size(max = 30, message = "Status must be at most 30 characters")
	private String status;

	public String getFirstName() {
		return firstName;
	}

	public void setFirstName(String firstName) {
		this.firstName = firstName;
	}

	public String getLastName() {
		return lastName;
	}

	public void setLastName(String lastName) {
		this.lastName = lastName;
	}

	public String getEmail() {
		return email;
	}

	public void setEmail(String email) {
		this.email = email;
	}

	public String getPhone() {
		return phone;
	}

	public void setPhone(String phone) {
		this.phone = phone;
	}

	public String getDepartment() {
		return department;
	}

	public void setDepartment(String department) {
		this.department = department;
	}

	public String getDesignation() {
		return designation;
	}

	public void setDesignation(String designation) {
		this.designation = designation;
	}

	public BigDecimal getSalary() {
		return salary;
	}

	public void setSalary(BigDecimal salary) {
		this.salary = salary;
	}

	public LocalDate getJoiningDate() {
		return joiningDate;
	}

	public void setJoiningDate(LocalDate joiningDate) {
		this.joiningDate = joiningDate;
	}

	public String getStatus() {
		return status;
	}

	public void setStatus(String status) {
		this.status = status;
	}
}
