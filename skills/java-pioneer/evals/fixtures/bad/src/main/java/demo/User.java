package demo;
import jakarta.persistence.*;
import lombok.Data;

@Data
@Entity
public class User {
    @Id private Long id;
    private String email;
    private String passwordHash;
    @ManyToOne private Team team;
}
