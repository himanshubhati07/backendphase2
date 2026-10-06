package com.example.studentmanagement.config;

import com.example.studentmanagement.controller.StudentController;
import com.example.studentmanagement.dto.StudentPageResponse;
import com.example.studentmanagement.filter.CorrelationIdFilter;
import com.example.studentmanagement.security.CustomUserDetailsService;
import com.example.studentmanagement.security.JwtAuthenticationFilter;
import com.example.studentmanagement.security.JwtService;
import com.example.studentmanagement.service.StudentService;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(StudentController.class)
@Import({SecurityConfig.class, CorrelationIdFilter.class, JwtAuthenticationFilter.class})
class SecurityAuthorizationTest {
    @Autowired private MockMvc mvc;
    @MockitoBean private StudentService studentService;
    @MockitoBean private JwtService jwtService;
    @MockitoBean private CustomUserDetailsService userDetailsService;

    @Test void unauthenticatedStudentRequestReturnsCorrelatedJson401() throws Exception {
        mvc.perform(get("/api/v1/students").header("X-Request-ID", "request-401"))
                .andExpect(status().isUnauthorized()).andExpect(header().string("X-Request-ID", "request-401"))
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED")).andExpect(jsonPath("$.status").value(401))
                .andExpect(jsonPath("$.correlationId").value("request-401"));
    }

    @Test @WithMockUser(roles = "USER") void nonAdminRequestReturnsCorrelatedJson403() throws Exception {
        mvc.perform(get("/api/v1/students").header("X-Request-ID", "request-403"))
                .andExpect(status().isForbidden()).andExpect(jsonPath("$.code").value("FORBIDDEN"))
                .andExpect(jsonPath("$.status").value(403)).andExpect(jsonPath("$.correlationId").value("request-403"));
    }

    @Test @WithMockUser(roles = "ADMIN") void adminCanAccessStudentResource() throws Exception {
        when(studentService.list(0, 20)).thenReturn(new StudentPageResponse(List.of(), 0, 20, 0));

        mvc.perform(get("/api/v1/students").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }
}
