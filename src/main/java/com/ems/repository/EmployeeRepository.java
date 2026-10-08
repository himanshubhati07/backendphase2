package com.ems.repository;

import com.ems.entity.Employee;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/**
 * Spring Data repository for {@link Employee}.
 */
public interface EmployeeRepository extends JpaRepository<Employee, Long> {

	boolean existsByEmail(String email);

	boolean existsByEmailAndIdNot(String email, Long id);

	/**
	 * Filters by name (matched against first OR last name), email, and department,
	 * case-insensitively. Any parameter left {@code null} is not filtered on at all.
	 */
	// Parameters are explicitly cast to `string` because PostgreSQL's JDBC driver cannot
	// infer a type for a bind parameter used only in a null-check ("? is null"), and
	// without the cast it defaults to a binary type - producing
	// "function lower(bytea) does not exist" the moment that same parameter also feeds
	// into lower(...) below.
	@Query("""
			select e from Employee e where
			(cast(:name as string) is null or lower(e.firstName) like lower(concat('%', cast(:name as string), '%'))
				or lower(e.lastName) like lower(concat('%', cast(:name as string), '%')))
			and (cast(:email as string) is null or lower(e.email) like lower(concat('%', cast(:email as string), '%')))
			and (cast(:department as string) is null
				or lower(e.department) like lower(concat('%', cast(:department as string), '%')))
			""")
	Page<Employee> search(
			@Param("name") String name,
			@Param("email") String email,
			@Param("department") String department,
			Pageable pageable);
}
