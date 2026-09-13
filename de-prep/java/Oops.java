import java.util.*;

public class Oops {
    public static void main(String... args){  // Variable Arguments
        System.out.println("hey");
        checkItOut();
    }

    public static void checkItOut(){
        List<Integer> newList = Arrays.asList(1,2,3,4);

        newList.stream().map(i -> i%2).forEach(System.out::println);
    }
}

/**
 * 1. true and true since Integer is a reference DT, both a,b and c,d point to their allocated values.
 * 2. unboxing is ok. If it runs then it means that null is converted to 0 (default int value)
 * when unboxed or else if null cant be converted to 0 or something, it'll throw compile time error.
 * 3. It will compile. Here we create a list with final keyword that means the reference can't be changed. i.e., it should point to another value.
 * 4. I haven't seen anything about init() yet. And I'm a bit off with inner classes.
 * 5. even if we dont use super(), it will exist in child constr. so, it'll print Parent and then Child
 */ 