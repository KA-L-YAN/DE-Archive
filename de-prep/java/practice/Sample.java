import java.util.*;
import java.util.stream.Collector;
import java.util.stream.Collectors;

public class Sample {

    public static <T> void print(T t){
        System.out.println(t);
    }

    public static void main(String... args){
        List<Integer> l = Arrays.asList(1,2,3,4,5,6,7,8,9,21,43,45,76,78);
        List<String> str = Arrays.asList("pavan", "kalyan","Aruna","Bhaskar","java");
        Sample s = new Sample();
        // s.check(l, 55);
        s.evens(Arrays.asList(1,1,1,1,1,1));

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
        print(list.stream().filter(i -> i==key).findFirst().isPresent());
        print(list.stream().anyMatch(i -> i==key));
    }

    public void evens(List<Integer> list){
        print(list.stream().filter(i -> i%2==0).map(String::valueOf).collect(Collectors.joining(",")));
        Map<Boolean, List<Integer>> checkers = list.stream().collect(Collectors.partitioningBy(i -> i%2==0));
        List<Integer> even = checkers.get(true);
        List<Integer> odd = checkers.get(false);
        print(even+"+"+odd);
    }

    public void upperCase(List<String> string){
        string.stream().map(String::toUpperCase).collect(Collectors.joining(":"));
        string.stream().map(String::toLowerCase).collect(Collectors.toList());
    }

    public void squares(List<Integer> list){
        list.stream().map(i->i*i).collect(Collectors.toList());
    }

    public void findFirstt(List<Integer> list){
        list.stream().findFirst().orElse(0);
    }

    public void findLast(List<Integer> list) {
        list.stream().reduce((i,j) -> j).orElse(0);
    }

    public void checkAll(List<Integer> list) {
        list.stream().allMatch(n -> n%2==0);
        list.stream().anyMatch(n-> n%2==0);
    }

    public void removeDups(List<Integer> list){
        Set<Integer> unq = list.stream().distinct().collect(Collectors.toSet());
    }

    public void sortt(List<Integer> list){
        list.stream().mapToInt(Integer::intValue).sorted();   // Cant sort a intStream in reverse order. Change it Integer Stream and then sort it in desc...
        list.stream().sorted().collect(Collectors.toList());
        list.stream().sorted(Comparator.reverseOrder()).collect(Collectors.toList());
    }

    public void sortStrings(List<String> str){
        str.stream().sorted().collect(Collectors.toList());

        str.stream().sorted(Comparator.comparingInt(i -> i.length())).collect(Collectors.toList());
        str.stream().sorted(Comparator.comparingInt(String::length)).collect(Collectors.joining("-"));
    }
    
    public void findSumOfDigits(int n){
        String.valueOf(n).stream().mapT
    }

}