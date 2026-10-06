package com.example.studentmanagement.kafka;

import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;

@Component
public class StudentEventConsumer {
    static final String TOPIC = "student-events";
    private static final Logger LOGGER = LoggerFactory.getLogger(StudentEventConsumer.class);

    private final AtomicLong consumedEventCount = new AtomicLong();
    private final AtomicReference<StudentEvent> lastConsumedEvent = new AtomicReference<>();

    @KafkaListener(topics = TOPIC, groupId = "${app.kafka.consumer-group}")
    public void consume(@Payload(required = false) StudentEvent event) {
        if (event == null) {
            LOGGER.warn("Ignoring malformed student event with no deserializable payload");
            return;
        }

        lastConsumedEvent.set(event);
        long count = consumedEventCount.incrementAndGet();
        LOGGER.info("Consumed student event type={} studentId={} count={}",
                event.type(), event.studentId(), count);
    }

    public long consumedEventCount() {
        return consumedEventCount.get();
    }

    public Optional<StudentEvent> lastConsumedEvent() {
        return Optional.ofNullable(lastConsumedEvent.get());
    }
}
