package com.example.studentmanagement.service;

import com.example.studentmanagement.dto.StudentRequest;
import com.example.studentmanagement.entity.Student;
import com.example.studentmanagement.exception.StudentNotFoundException;
import com.example.studentmanagement.kafka.StudentEvent;
import com.example.studentmanagement.kafka.StudentEventType;
import com.example.studentmanagement.repository.StudentRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.data.domain.PageImpl;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class StudentServiceTest {
    private final StudentRepository repository = mock(StudentRepository.class);
    private final ApplicationEventPublisher eventPublisher = mock(ApplicationEventPublisher.class);
    private final StudentService service = new StudentService(repository, eventPublisher);
    private final StudentRequest request = new StudentRequest("Ada", "ada@example.com", "123", "Math", 20);

    @Test
    void createPersistsThenPublishesCreateApplicationEvent() {
        when(repository.saveAndFlush(any(Student.class))).thenAnswer(call -> call.getArgument(0));

        service.create(request);

        ArgumentCaptor<StudentEvent> event = ArgumentCaptor.forClass(StudentEvent.class);
        verify(eventPublisher).publishEvent(event.capture());
        assertEquals(StudentEventType.CREATE, event.getValue().type());
    }

    @Test
    void listDelegatesExactOffsetPageable() {
        when(repository.findAll(any(OffsetLimitPageable.class))).thenReturn(new PageImpl<>(List.of()));

        assertEquals(7, service.list(7, 20).offset());
        verify(repository).findAll(any(OffsetLimitPageable.class));
    }

    @Test
    void getMissingThrowsDomainException() {
        when(repository.findById(9L)).thenReturn(Optional.empty());

        assertThrows(StudentNotFoundException.class, () -> service.get(9L));
    }

    @Test
    void updatePublishesUpdateApplicationEvent() {
        Student student = new Student("Old", "old@example.com", "1", "Old", 19);
        when(repository.findById(1L)).thenReturn(Optional.of(student));
        when(repository.saveAndFlush(student)).thenReturn(student);

        service.update(1L, request);

        ArgumentCaptor<Object> event = ArgumentCaptor.forClass(Object.class);
        verify(eventPublisher).publishEvent(event.capture());
        assertEquals(StudentEventType.UPDATE, ((StudentEvent) event.getValue()).type());
    }

    @Test
    void deletePublishesDeleteApplicationEvent() {
        Student student = new Student("Ada", "ada@example.com", "1", "Math", 20);
        when(repository.findById(1L)).thenReturn(Optional.of(student));

        service.delete(1L);

        verify(repository).deleteById(1L);
        verify(repository).flush();
        ArgumentCaptor<Object> event = ArgumentCaptor.forClass(Object.class);
        verify(eventPublisher).publishEvent(event.capture());
        assertEquals(StudentEventType.DELETE, ((StudentEvent) event.getValue()).type());
    }
}
