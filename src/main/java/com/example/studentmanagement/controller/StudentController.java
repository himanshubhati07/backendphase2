package com.example.studentmanagement.controller;

import com.example.studentmanagement.dto.StudentPageResponse;
import com.example.studentmanagement.dto.StudentRequest;
import com.example.studentmanagement.dto.StudentResponse;
import com.example.studentmanagement.service.StudentService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Positive;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/students")
public class StudentController {
    private final StudentService studentService;
    public StudentController(StudentService studentService) { this.studentService = studentService; }
    @PostMapping @ResponseStatus(HttpStatus.CREATED) public StudentResponse create(@Valid @RequestBody StudentRequest request) { return studentService.create(request); }
    @GetMapping public StudentPageResponse list(@RequestParam(defaultValue = "0") @Min(0) long offset, @RequestParam(defaultValue = "20") @Positive int limit) { return studentService.list(offset, limit); }
    @GetMapping("/{id}") public StudentResponse get(@PathVariable Long id) { return studentService.get(id); }
    @PutMapping("/{id}") public StudentResponse update(@PathVariable Long id, @Valid @RequestBody StudentRequest request) { return studentService.update(id, request); }
    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT) public void delete(@PathVariable Long id) { studentService.delete(id); }
}
