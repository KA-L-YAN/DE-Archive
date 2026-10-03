import java.util.*;

public class Sample {

    public static <T> void print(T t){
        System.out.println(t);
    }

    public static void main(String... args){

    }

    public void sum(List<Integer> list){
        list.stream().mapToInt(Integer::intValue).sum();
        list.stream().mapToInt(i -> i.intValue()).sum();
    }

}