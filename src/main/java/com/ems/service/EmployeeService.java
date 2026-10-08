package com.ems.service;

import com.ems.dto.EmployeeRequest;
import com.ems.dto.EmployeeResponse;
import com.ems.dto.PageResponse;
import com.ems.entity.Employee;
import com.ems.exception.DuplicateResourceException;
import com.ems.exception.ResourceNotFoundException;
import com.ems.repository.EmployeeRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Business logic for managing employees: creation, lookup, paginated listing,
 * updates, deletion, and multi-field search.
 */
@Service
@Transactional
public class EmployeeService {

	private static final Logger log = LoggerFactory.getLogger(EmployeeService.class);

	private final EmployeeRepository employeeRepository;

	public EmployeeService(EmployeeRepository employeeRepository) {
		this.employeeRepository = employeeRepository;
	}

	public EmployeeResponse create(EmployeeRequest request) {
		if (employeeRepository.existsByEmail(request.getEmail())) {
			throw new DuplicateResourceException(
					"An employee with email '" + request.getEmail() + "' already exists");
		}
		Employee employee = new Employee(
				request.getFirstName(),
				request.getLastName(),
				request.getEmail(),
				request.getPhone(),
				request.getDepartment(),
				request.getDesignation(),
				request.getSalary(),
				request.getJoiningDate(),
				request.getStatus());
		Employee saved = employeeRepository.save(employee);
		log.info("Created employee id={}", saved.getId());
		return EmployeeResponse.fromEntity(saved);
	}

	@Transactional(readOnly = true)
	public EmployeeResponse getById(Long id) {
		return EmployeeResponse.fromEntity(findEmployeeOrThrow(id));
	}

	@Transactional(readOnly = true)
	public PageResponse<EmployeeResponse> list(int page, int limit) {
		Page<Employee> result = employeeRepository.findAll(PageRequest.of(page, limit));
		return PageResponse.of(result, EmployeeResponse::fromEntity);
	}

	public EmployeeResponse update(Long id, EmployeeRequest request) {
		Employee employee = findEmployeeOrThrow(id);
		if (employeeRepository.existsByEmailAndIdNot(request.getEmail(), id)) {
			throw new DuplicateResourceException(
					"An employee with email '" + request.getEmail() + "' already exists");
		}
		applyRequest(employee, request);
		Employee saved = employeeRepository.save(employee);
		log.info("Updated employee id={}", saved.getId());
		return EmployeeResponse.fromEntity(saved);
	}

	public void delete(Long id) {
		if (!employeeRepository.existsById(id)) {
			throw new ResourceNotFoundException("Employee not found: id=" + id);
		}
		employeeRepository.deleteById(id);
		log.info("Deleted employee id={}", id);
	}

	@Transactional(readOnly = true)
	public PageResponse<EmployeeResponse> search(
			String name, String email, String department, int page, int limit) {
		Page<Employee> result = employeeRepository.search(
				blankToNull(name), blankToNull(email), blankToNull(department), PageRequest.of(page, limit));
		return PageResponse.of(result, EmployeeResponse::fromEntity);
	}

	private Employee findEmployeeOrThrow(Long id) {
		return employeeRepository
				.findById(id)
				.orElseThrow(() -> new ResourceNotFoundException("Employee not found: id=" + id));
	}

	private void applyRequest(Employee employee, EmployeeRequest request) {
		employee.setFirstName(request.getFirstName());
		employee.setLastName(request.getLastName());
		employee.setEmail(request.getEmail());
		employee.setPhone(request.getPhone());
		employee.setDepartment(request.getDepartment());
		employee.setDesignation(request.getDesignation());
		employee.setSalary(request.getSalary());
		employee.setJoiningDate(request.getJoiningDate());
		employee.setStatus(request.getStatus());
	}

	private String blankToNull(String value) {
		return (value == null || value.isBlank()) ? null : value.trim();
	}
}
