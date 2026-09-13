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
        print(set.conta)

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
