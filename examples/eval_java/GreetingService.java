public class GreetingService {
    public String greet(String name) {
        if (name == null || name.isEmpty() || name.length() > Config.MAX_NAME_LENGTH) {
            throw new IllegalArgumentException("Invalid name");
        }
        return "Hello, " + name + "!";
    }
}
