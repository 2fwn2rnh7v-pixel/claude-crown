package demo;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Optional;

@RestController
public class UserController {
    @Autowired UserRepository repo;
    @Autowired jakarta.persistence.EntityManager em;

    @GetMapping("/users")
    public List<User> all(@RequestParam String sort) {
        return repo.findAll(Sort.by(sort));
    }

    @GetMapping("/search")
    public List<User> search(@RequestParam String email) {
        return em.createQuery("select u from User u where u.email = '" + email + "'", User.class).getResultList();
    }

    @PostMapping("/users")
    public User create(@RequestBody User u, Optional<String> note) {
        try { return repo.save(u); } catch (Exception e) { e.printStackTrace(); }
        return null;
    }
}
