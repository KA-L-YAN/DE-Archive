package practice;
import java.util.*;

public class Collectionz {

    public static <T> void print(T t) {
    System.out.println(t);
    }

    public static void main(String... args){
        List<String> strings = new LinkedList<>(List.of("Pavan","Kalyan"));
        strings.add("nayak");
        List<String> str = new ArrayList<>();
        str.add("pavan");
        ListIterator<String> it = str.listIterator();
        while(it.hasNext()){
            if(it.next() == "pavan"){
                it.remove();
            }
        }
        print(strings);
        strings.removeIf(i-> i=="Kalyan");
        print(strings);
    }
    
}
