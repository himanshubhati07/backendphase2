package com.example.studentmanagement.kafka;

import com.example.studentmanagement.dto.StudentResponse;
import java.time.Instant;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.Test;
import org.springframework.kafka.core.KafkaTemplate;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class StudentEventProducerTest {
    @Test
    void publishesStudentEventAsTheValueToTheStudentEventsTopic() {
        KafkaTemplate<String, StudentEvent> kafkaTemplate = mock(KafkaTemplate.class);
        StudentEvent event = new StudentEvent(StudentEventType.CREATE, 1L,
                Instant.parse("2025-01-01T00:00:00Z"), student());
        when(kafkaTemplate.send("student-events", "1", event)).thenReturn(new CompletableFuture<>());
        StudentEventProducer producer = new StudentEventProducer(kafkaTemplate);

        producer.publish(event);

        verify(kafkaTemplate).send("student-events", "1", event);
    }

    private StudentResponse student() {
        return new StudentResponse(1L, "Ada", "ada@example.com", "123", "Math", 20);
    }
}
