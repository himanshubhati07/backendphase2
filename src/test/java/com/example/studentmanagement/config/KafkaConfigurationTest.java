package com.example.studentmanagement.config;

import java.util.Properties;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;
import org.springframework.kafka.support.serializer.JsonDeserializer;
import org.springframework.kafka.support.serializer.JsonSerializer;
import org.springframework.beans.factory.config.YamlPropertiesFactoryBean;
import static org.junit.jupiter.api.Assertions.assertEquals;

class KafkaConfigurationTest {
    @Test
    void configuresJsonSerializationForStudentEvents() {
        YamlPropertiesFactoryBean yaml = new YamlPropertiesFactoryBean();
        yaml.setResources(new ClassPathResource("application.yml"));
        Properties properties = yaml.getObject();

        assertEquals(JsonSerializer.class.getName(), properties.getProperty("spring.kafka.producer.value-serializer"));
        assertEquals(JsonDeserializer.class.getName(), properties.getProperty("spring.kafka.consumer.value-deserializer"));
        assertEquals("com.example.studentmanagement.kafka.StudentEvent",
                properties.getProperty("spring.kafka.consumer.properties.spring.json.value.default.type"));
    }
}
