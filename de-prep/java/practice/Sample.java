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
    }

    public void max(List<Integer> list){
        list.stream().mapToInt(Integer::intValue).max();
        list.stream().max(Integer::compare).orElse(0);
        list.stream().max(Integer::compareTo).orElse(0);
    }

    public void min(List<Integer> list){
        list.stream().min(Integer::compareTo).get();
        list.stream().min(Integer::compare).get();
        list.stream().mapToInt(Integer::intValue).min();
    }

    public void count(List<Integer> list){
        list.stream().count();
    }

    public void check(List<Integer> list, int key){
        list.stream().anyMatch(i -> i==key);
        list.stream().filter(i -> i==key).findFirst().isPresent();
        list.stream().anyMatch(i -> i==key);
    }
}