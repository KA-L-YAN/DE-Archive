import java.util.*;

public class Basics {

    int x,y;
    
    public static <T> void print(T t){
        System.out.println(t);
    }

    public static void main (String... args){
        print("We practice all the Java basics here.");
        Set<Basics> setb = new HashSet<>();
        setb.add(new Basics(1,2));
        print(setb.contains(new Basics(1,2)));

    }

    Basics(int x, int y){
        this.x= x;
        this.y = y;
    }

    @Override 
    public boolean equals(Object o){
        if(!(o instanceof Basics)) return false;
        Basics b = (Basics) o;
        return x == b.x && y == b.y;
    }

}


/**
 * 1. I have tried it out and it print false. the equal seems correct but here why I think it print false,
 * We have added 1,2 to the set with add() with one anonymous object and the we created another anonymous object to check if 1 and 2 exist or not.
 * 2. No, can you please explain this. I have always had doubts around this concept...
 * 3. Animal and woof! ( when we create an object of type Animal referencing to the Dog class, the compiler checks for super class methods implementation in the change class and thats why woof was printed since it has overridden speak() method of parent class)
 * This has nothing to do with the name variable
 * 4. Base init
 * 5. no.
 * 6. Yes. but super() should be in the first line of the constructor
 */
