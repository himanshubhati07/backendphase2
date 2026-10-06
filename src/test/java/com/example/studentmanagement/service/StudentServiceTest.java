package com.example.studentmanagement.service;

import com.example.studentmanagement.dto.StudentRequest;
import com.example.studentmanagement.entity.Student;
import com.example.studentmanagement.exception.StudentNotFoundException;
import com.example.studentmanagement.kafka.StudentEvent;
import com.example.studentmanagement.kafka.StudentEventProducer;
import com.example.studentmanagement.kafka.StudentEventType;
import com.example.studentmanagement.repository.StudentRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class StudentServiceTest {
    private final StudentRepository repository = mock(StudentRepository.class);
    private final StudentEventProducer producer = mock(StudentEventProducer.class);
    private final StudentService service = new StudentService(repository, producer);
    private final StudentRequest request = new StudentRequest("Ada", "ada@example.com", "123", "Math", 20);
    @Test void createPersistsThenPublishesCreate() {
        when(repository.saveAndFlush(any(Student.class))).thenAnswer(call -> call.getArgument(0));
        service.create(request);
        ArgumentCaptor<StudentEvent> event = ArgumentCaptor.forClass(StudentEvent.class);
        verify(producer).publish(event.capture()); assertEquals(StudentEventType.CREATE, event.getValue().type());
    }
    @Test void listDelegatesExactOffsetPageable() {
        when(repository.findAll(any(OffsetLimitPageable.class))).thenReturn(new PageImpl<>(List.of()));
        assertEquals(7, service.list(7, 20).offset()); verify(repository).findAll(any(OffsetLimitPageable.class));
    }
    @Test void getMissingThrowsDomainException() { when(repository.findById(9L)).thenReturn(Optional.empty()); assertThrows(StudentNotFoundException.class, () -> service.get(9L)); }
    @Test void updatePublishesUpdate() {
        Student student = new Student("Old", "old@example.com", "1", "Old", 19); when(repository.findById(1L)).thenReturn(Optional.of(student)); when(repository.saveAndFlush(student)).thenReturn(student);
        service.update(1L, request); verify(producer).publish(org.mockito.ArgumentMatchers.argThat(event -> event.type() == StudentEventType.UPDATE));
    }
    @Test void deletePublishesDelete() {
        Student student = new Student("Ada", "ada@example.com", "1", "Math", 20); when(repository.findById(1L)).thenReturn(Optional.of(student));
        service.delete(1L); verify(repository).deleteById(1L); verify(repository).flush(); verify(producer).publish(org.mockito.ArgumentMatchers.argThat(event -> event.type() == StudentEventType.DELETE));
    }
}
