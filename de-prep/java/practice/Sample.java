import java.util.*;
import java.util.stream.Collector;
import java.util.stream.Collectors;

public class Sample {

    public static <T> void print(T t){
        System.out.println(t);
    }

    public static void main(String... args){

    }

    public void sum(List<Integer> list){
        list.stream().mapToInt(Integer::intValue).sum();
        list.stream().mapToInt(i -> i.intValue()).sum();
        list.stream().reduce(0,Integer::sum);
    }

    public void product(List<Integer> list){
        list.stream().reduce(1, (a,b) -> a*b);
        Optional<Integer> product = list.stream().reduce((a,b) -> a*b);
        print(product);
        list.stream().collect(Collectors.reducing(1, (a,b) -> a*b));
    }

    public void average(Set<Integer> set){
        set.stream().mapToInt(Integer::intValue).average().orElse(0);
        set.stream().reduce()
    }

}