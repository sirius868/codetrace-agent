public class App {
    public static void main(String[] args) {
        try {
            System.out.println(new GreetingService().greet("CodeTrace"));
        } catch (IllegalArgumentException e) {
            System.out.println("Invalid name");
        }
    }
}
