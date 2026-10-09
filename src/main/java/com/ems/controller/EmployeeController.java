package com.ems.controller;

import com.ems.dto.ApiResponse;
import com.ems.dto.EmployeeRequest;
import com.ems.dto.EmployeeResponse;
import com.ems.dto.PageResponse;
import com.ems.service.EmployeeService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST endpoints for managing employees. Every endpoint here requires a valid JWT,
 * enforced globally by {@code SecurityConfig}'s {@code anyRequest().authenticated()}
 * rule.
 */
@RestController
@RequestMapping("/api/v1/employees")
@Tag(name = "Employees", description = "Employee management")
public class EmployeeController {

	private final EmployeeService employeeService;

	public EmployeeController(EmployeeService employeeService) {
		this.employeeService = employeeService;
	}

	@PostMapping
	@Operation(summary = "Create a new employee")
	public ResponseEntity<ApiResponse<EmployeeResponse>> create(@Valid @RequestBody EmployeeRequest request) {
		EmployeeResponse created = employeeService.create(request);
		return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(created));
	}

	@GetMapping("/{id}")
	@Operation(summary = "Get an employee by id")
	public ResponseEntity<ApiResponse<EmployeeResponse>> getById(@PathVariable Long id) {
		return ResponseEntity.ok(ApiResponse.success(employeeService.getById(id)));
	}

	@GetMapping
	@Operation(summary = "List all employees, offset-paginated")
	public ResponseEntity<ApiResponse<PageResponse<EmployeeResponse>>> list(
			@RequestParam(defaultValue = "0") int page, @RequestParam(defaultValue = "20") int limit) {
		return ResponseEntity.ok(ApiResponse.success(employeeService.list(page, limit)));
	}

	@GetMapping("/search")
	@Operation(summary = "Search employees by name, email, or department")
	public ResponseEntity<ApiResponse<PageResponse<EmployeeResponse>>> search(
			@RequestParam(required = false) String name,
			@RequestParam(required = false) String email,
			@RequestParam(required = false) String department,
			@RequestParam(defaultValue = "0") int page,
			@RequestParam(defaultValue = "20") int limit) {
		return ResponseEntity.ok(ApiResponse.success(employeeService.search(name, email, department, page, limit)));
	}

	@PutMapping("/{id}")
	@Operation(summary = "Update an existing employee")
	public ResponseEntity<ApiResponse<EmployeeResponse>> update(
			@PathVariable Long id, @Valid @RequestBody EmployeeRequest request) {
		return ResponseEntity.ok(ApiResponse.success(employeeService.update(id, request)));
	}
}
