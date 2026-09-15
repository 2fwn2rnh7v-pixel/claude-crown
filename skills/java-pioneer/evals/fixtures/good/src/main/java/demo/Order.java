package demo;
import jakarta.persistence.*;
import java.util.UUID;

@Entity
public class Order {
    @Id private UUID id;
    @ManyToOne(fetch = FetchType.LAZY) private Customer customer;
    protected Order() {}
}
