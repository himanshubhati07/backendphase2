package com.example.studentmanagement.kafka;

import com.example.studentmanagement.dto.StudentResponse;
import java.lang.reflect.Method;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.kafka.annotation.KafkaListener;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class StudentEventConsumerTest {
    @Test
    void listensToStudentEventsWithTheConfiguredConsumerGroup() throws NoSuchMethodException {
        Method method = StudentEventConsumer.class.getMethod("consume", StudentEvent.class);
        KafkaListener listener = method.getAnnotation(KafkaListener.class);

        assertArrayEquals(new String[]{"student-events"}, listener.topics());
        assertEquals("${app.kafka.consumer-group}", listener.groupId());
    }

    @Test
    void recordsSuccessfullyConsumedStudentEvents() {
        StudentEventConsumer consumer = new StudentEventConsumer();
        StudentEvent event = event();

        consumer.consume(event);

        assertEquals(1, consumer.consumedEventCount());
        assertTrue(consumer.lastConsumedEvent().isPresent());
        assertEquals(event, consumer.lastConsumedEvent().orElseThrow());
    }

    @Test
    void ignoresUndeserializablePayloadsWithoutFailingTheListener() {
        StudentEventConsumer consumer = new StudentEventConsumer();

        assertDoesNotThrow(() -> consumer.consume(null));

        assertEquals(0, consumer.consumedEventCount());
        assertFalse(consumer.lastConsumedEvent().isPresent());
    }

    private StudentEvent event() {
        StudentResponse student = new StudentResponse(1L, "Ada", "ada@example.com", "123", "Math", 20);
        return new StudentEvent(StudentEventType.CREATE, 1L, Instant.parse("2025-01-01T00:00:00Z"), student);
    }
}
