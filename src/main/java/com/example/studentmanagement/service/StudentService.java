package com.example.studentmanagement.service;

import com.example.studentmanagement.dto.StudentPageResponse;
import com.example.studentmanagement.dto.StudentRequest;
import com.example.studentmanagement.dto.StudentResponse;
import com.example.studentmanagement.entity.Student;
import com.example.studentmanagement.exception.StudentNotFoundException;
import com.example.studentmanagement.kafka.StudentEvent;
import com.example.studentmanagement.kafka.StudentEventProducer;
import com.example.studentmanagement.kafka.StudentEventType;
import com.example.studentmanagement.repository.StudentRepository;
import java.time.Instant;
import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class StudentService {
    private final StudentRepository studentRepository;
    private final StudentEventProducer eventProducer;
    public StudentService(StudentRepository studentRepository, StudentEventProducer eventProducer) { this.studentRepository = studentRepository; this.eventProducer = eventProducer; }
    @Transactional public StudentResponse create(StudentRequest request) {
        Student saved = studentRepository.saveAndFlush(new Student(request.name(), request.email(), request.phone(), request.course(), request.age()));
        StudentResponse response = toResponse(saved); publish(StudentEventType.CREATE, response); return response;
    }
    @Transactional(readOnly = true) public StudentPageResponse list(long offset, int limit) {
        Page<Student> page = studentRepository.findAll(new OffsetLimitPageable(offset, limit));
        List<StudentResponse> items = page.getContent().stream().map(this::toResponse).toList();
        return new StudentPageResponse(items, page.getTotalElements(), limit, offset);
    }
    @Transactional(readOnly = true) public StudentResponse get(Long id) { return toResponse(require(id)); }
    @Transactional public StudentResponse update(Long id, StudentRequest request) {
        Student student = require(id); student.replace(request.name(), request.email(), request.phone(), request.course(), request.age());
        StudentResponse response = toResponse(studentRepository.saveAndFlush(student)); publish(StudentEventType.UPDATE, response); return response;
    }
    @Transactional public void delete(Long id) {
        StudentResponse response = toResponse(require(id)); studentRepository.deleteById(id); studentRepository.flush(); publish(StudentEventType.DELETE, response);
    }
    private Student require(Long id) { return studentRepository.findById(id).orElseThrow(() -> new StudentNotFoundException(id)); }
    private StudentResponse toResponse(Student student) { return new StudentResponse(student.getId(), student.getName(), student.getEmail(), student.getPhone(), student.getCourse(), student.getAge()); }
    private void publish(StudentEventType type, StudentResponse student) { eventProducer.publish(new StudentEvent(type, student.id(), Instant.now(), student)); }
}
