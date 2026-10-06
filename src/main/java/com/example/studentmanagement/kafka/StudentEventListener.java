package com.example.studentmanagement.kafka;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class StudentEventListener {
    private static final Logger LOGGER = LoggerFactory.getLogger(StudentEventListener.class);
    @KafkaListener(topics = "student-events")
    public void consume(StudentEvent event) { LOGGER.info("Consumed student event type={} studentId={}", event.type(), event.studentId()); }
}
