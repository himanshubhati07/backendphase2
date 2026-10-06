package com.example.studentmanagement.exception;

import com.example.studentmanagement.controller.AuthController;
import com.example.studentmanagement.controller.StudentController;
import com.example.studentmanagement.filter.CorrelationIdFilter;
import com.example.studentmanagement.service.AuthService;
import com.example.studentmanagement.service.StudentService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ErrorResponseTest {
    private AuthService authService;
    private StudentService studentService;
    private MockMvc mvc;

    @BeforeEach void setup() {
        authService = mock(AuthService.class);
        studentService = mock(StudentService.class);
        mvc = MockMvcBuilders.standaloneSetup(new AuthController(authService), new StudentController(studentService))
                .setControllerAdvice(new GlobalExceptionHandler()).addFilters(new CorrelationIdFilter()).build();
    }

    @Test void validationFailureReturnsCorrelated400() throws Exception {
        mvc.perform(post("/api/v1/auth/login").header("X-Request-ID", "request-400")
                        .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("VALIDATION_ERROR"))
                .andExpect(jsonPath("$.status").value(400)).andExpect(jsonPath("$.correlationId").value("request-400"));
    }

    @Test void missingStudentReturnsCorrelated404() throws Exception {
        when(studentService.get(99L)).thenThrow(new StudentNotFoundException(99L));

        mvc.perform(get("/api/v1/students/99").header("X-Request-ID", "request-404"))
                .andExpect(status().isNotFound()).andExpect(jsonPath("$.code").value("NOT_FOUND"))
                .andExpect(jsonPath("$.status").value(404)).andExpect(jsonPath("$.correlationId").value("request-404"));
    }

    @Test void reusedRefreshTokenReturnsCorrelated409() throws Exception {
        doThrow(new InvalidRefreshTokenException("Refresh token has been revoked")).when(authService).refresh("reused-token");

        mvc.perform(post("/api/v1/auth/refresh").header("X-Request-ID", "request-409")
                        .contentType(MediaType.APPLICATION_JSON).content("{\"refreshToken\":\"reused-token\"}"))
                .andExpect(status().isConflict()).andExpect(jsonPath("$.code").value("INVALID_REFRESH_TOKEN"))
                .andExpect(jsonPath("$.status").value(409)).andExpect(jsonPath("$.correlationId").value("request-409"));
    }
}
